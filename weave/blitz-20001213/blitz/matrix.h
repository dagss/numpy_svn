/***************************************************************************
 * blitz/matrix.h      Declaration of the Matrix<T_type, T_structure> class
 *
 * $Id$
 *
 * Copyright (C) 1997-1999 Todd Veldhuizen <tveldhui@oonumerics.org>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * Suggestions:          blitz-dev@oonumerics.org
 * Bugs:                 blitz-bugs@oonumerics.org
 *
 * For more information, please see the Blitz++ Home Page:
 *    http://oonumerics.org/blitz/
 *
 ***************************************************************************
 * $Log$
 * Revision 1.1  2002/01/03 19:50:34  eric
 * renaming compiler to weave
 *
 * Revision 1.1  2001/04/27 17:22:04  ej
 * first attempt to include needed pieces of blitz
 *
 * Revision 1.1.1.1  2000/06/19 12:26:11  tveldhui
 * Imported sources
 *
 * Revision 1.6  1998/03/14 00:04:47  tveldhui
 * 0.2-alpha-05
 *
 * Revision 1.5  1997/07/16 14:51:20  tveldhui
 * Update: Alpha release 0.2 (Arrays)
 *
 * Revision 1.4  1997/01/24 14:42:00  tveldhui
 * Periodic RCS update
 *
 * Revision 1.3  1997/01/23 03:28:28  tveldhui
 * Periodic RCS update
 *
 * Revision 1.2  1997/01/13 22:19:58  tveldhui
 * Periodic RCS update
 *
 * Revision 1.1  1996/11/11 17:29:13  tveldhui
 * Initial revision
 *
 * Revision 1.2  1996/10/31 21:06:54  tveldhui
 * Did away with multiple template parameters.  Only numeric type
 * and structure parameters now.
 *
 *
 */

#ifndef BZ_MATRIX_H
#define BZ_MATRIX_H

#ifndef BZ_BLITZ_H
 #include <blitz/blitz.h>
#endif

#ifndef BZ_MEMBLOCK_H
 #include <blitz/memblock.h>
#endif

#ifndef BZ_MSTRUCT_H
 #include <blitz/mstruct.h>
#endif

BZ_NAMESPACE(blitz)

// Forward declarations
template<class P_numtype, class P_structure>
class _bz_MatrixRef;

template<class P_expr>
class _bz_MatExpr;

// Declaration of class Matrix
template<class P_numtype, class P_structure BZ_TEMPLATE_DEFAULT(RowMajor)>
class Matrix : protected MemoryBlockReference<P_numtype> {

public:

    //////////////////////////////////////////////
    // Public Types
    //////////////////////////////////////////////

    typedef P_numtype        T_numtype;
    typedef P_structure      T_structure;
    typedef Matrix<P_numtype, P_structure>   T_matrix;

    //////////////////////////////////////////////
    // Constructors                             //
    //////////////////////////////////////////////

    Matrix()
    { }

    Matrix(int rows, int cols, T_structure structure = T_structure())
        : structure_(structure) 
    {
        structure_.resize(rows, cols);
        MemoryBlockReference<T_numtype>::newBlock(structure_.numElements());
    }

    // Matrix(int rows, int cols, T_numtype initValue,
    //    T_structure structure = T_structure(rows, cols));
    // Matrix(int rows, int cols, Random);
    // Matrix(int rows, int cols, matrix-expression);
    // Matrix(int rows, int cols, T_numtype* data, int rowStride, int colStride);
    // _bz_explicit Matrix(Vector<T_numtype>& matrix);
    // _bz_explicit Matrix(unsigned length);

    // Create a vector view of an already allocated block of memory.
    // Note that the memory will not be freed when this vector is
    // destroyed.
    // Matrix(unsigned length, T_numtype* data, int stride = 1);

    //////////////////////////////////////////////
    // Member functions
    //////////////////////////////////////////////

    //T_iterator      begin()  const;
    //T_constIterator begin()  const;
    //T_vector        copy()   const;
    //T_iterator      end()    const;
    //T_constIterator end()    const;

    unsigned        cols()        const
    { return structure_.columns(); }

    unsigned        columns()     const
    { return structure_.columns(); }

    void            makeUnique()  const;

    unsigned        numElements() const
    { return structure_.numElements(); }

    void            reference(T_matrix&);

    void            resize(unsigned rows, unsigned cols)
    {
        structure_.resize(rows, cols);
        MemoryBlockReference<T_numtype>::newBlock(structure_.numElements());
    }

//    void            resizeAndPreserve(unsigned newLength);

    unsigned        rows()   const
    { return structure_.rows(); }

    _bz_MatrixRef<T_numtype, T_structure> _bz_getRef() const
    { return _bz_MatrixRef<T_numtype, T_structure>(*this); }

    //////////////////////////////////////////////
    // Subscripting operators
    //////////////////////////////////////////////

    T_numtype           operator()(unsigned i, unsigned j) const
    {
        return structure_.get(data_, i, j);
    }

    T_numtype& _bz_restrict operator()(unsigned i, unsigned j)
    {
        return structure_.get(data_, i, j);
    }

    // T_matrix      operator()(Range,Range);

    // T_matrixIndirect operator()(Vector<int>,Vector<int>);
    // T_matrixIndirect operator()(integer-placeholder-expression, Range);
    // T_matrix         operator()(difference-equation-expression)

    //////////////////////////////////////////////
    // Assignment operators
    //////////////////////////////////////////////

    // Scalar operand
    T_matrix& operator=(T_numtype);
    T_matrix& operator+=(T_numtype);
    T_matrix& operator-=(T_numtype);
    T_matrix& operator*=(T_numtype);
    T_matrix& operator/=(T_numtype);

    // Matrix operand

    template<class P_numtype2, class P_structure2> 
    T_matrix& operator=(const Matrix<P_numtype2, P_structure2> &);
    template<class P_numtype2, class P_structure2> 
    T_matrix& operator+=(const Matrix<P_numtype2, P_structure2>&);
    template<class P_numtype2, class P_structure2> 
    T_matrix& operator-=(const Matrix<P_numtype2, P_structure2> &);
    template<class P_numtype2, class P_structure2> 
    T_matrix& operator*=(const Matrix<P_numtype2, P_structure2> &);
    template<class P_numtype2, class P_structure2> 
    T_matrix& operator/=(const Matrix<P_numtype2, P_structure2> &);

    // Matrix expression operand
    template<class P_expr>
    T_matrix& operator=(_bz_MatExpr<P_expr>);

    // Integer placeholder expression operand
    // MatrixPick operand

    //////////////////////////////////////////////
    // Unary operators
    //////////////////////////////////////////////

    T_matrix& operator++();
    void operator++(int);
    T_matrix& operator--();
    void operator--(int);
    
private:
    T_structure structure_;
};

template<class P_numtype, class P_structure>
ostream& operator<<(ostream& os, const Matrix<P_numtype, P_structure>& matrix);

// Global operators
// +,-,*,/ with all possible combinations of:
//    - scalar
//    - matrix
//    - matrix pick
//    - matrix expression
// Pointwise Math functions: sin, cos, etc.
// Global functions

BZ_NAMESPACE_END

#include <blitz/matrix.cc>
#include <blitz/matexpr.h>

#endif // BZ_MATRIX_H
